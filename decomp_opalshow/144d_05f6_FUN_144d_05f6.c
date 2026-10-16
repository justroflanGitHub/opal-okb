
void __cdecl16far FUN_144d_05f6(void)

{
  int *piVar1;
  char *pcVar2;
  char cVar3;
  int iVar4;
  int iVar5;
  int iVar6;
  undefined2 *puVar7;
  int *piVar8;
  char *pcVar9;
  undefined2 unaff_SS;
  undefined2 unaff_DS;
  
  iVar6 = 0;
  pcVar9 = (char *)0x0;
  iVar5 = -1;
  iVar4 = *(int *)0x2c;
  if (iVar4 != 0) {
    cVar3 = *(char *)0x0;
    while (cVar3 != '\0') {
      do {
        if (iVar5 == 0) break;
        iVar5 = iVar5 + -1;
        pcVar2 = pcVar9;
        pcVar9 = pcVar9 + 1;
      } while (*pcVar2 != '\0');
      iVar6 = iVar6 + 1;
      pcVar2 = pcVar9;
      pcVar9 = pcVar9 + 1;
      cVar3 = *pcVar2;
    }
  }
  iVar6 = iVar6 + 1;
  puVar7 = (undefined2 *)(iVar6 * 4);
  iVar5 = FUN_144d_06b6(iVar6,&stack0xfffe);
  pcVar9 = (char *)((int)puVar7 + iVar5);
  *(undefined2 *)0x3d6 = puVar7;
  *(undefined2 *)0x3d8 = unaff_SS;
  piVar8 = (int *)0x0;
  while (iVar6 = iVar6 + -1, iVar6 != 0) {
    if (*piVar8 != 0x433b) {
      *puVar7 = pcVar9;
      puVar7[1] = unaff_SS;
      puVar7 = puVar7 + 2;
    }
    do {
      piVar1 = piVar8;
      piVar8 = (int *)((int)piVar8 + 1);
      iVar5 = *piVar1;
      pcVar2 = pcVar9;
      pcVar9 = pcVar9 + 1;
      *pcVar2 = (char)iVar5;
    } while ((char)iVar5 != '\0');
  }
  *puVar7 = 0;
  puVar7[1] = 0;
  return;
}

