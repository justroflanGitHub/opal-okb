
void __cdecl16far FUN_1089_0106(void)

{
  code *pcVar1;
  int iVar2;
  undefined2 unaff_DS;
  undefined1 uVar3;
  undefined1 local_162 [21];
  byte local_14d;
  undefined1 local_144 [14];
  undefined1 local_136 [72];
  undefined1 local_ee [69];
  char acStack_a9 [71];
  undefined1 local_62 [12];
  char local_56 [84];
  
  FUN_1100_0138(0);
  FUN_1100_010e(0);
  FUN_15f4_0010(5,acStack_a9 + 1);
  FUN_15f4_0056(0,local_62);
  FUN_1089_04dc(acStack_a9 + 1);
  iVar2 = FUN_144d_09ce(0x928);
  if (iVar2 != 0) {
    *(undefined2 *)0x1608 = 0;
    while (*(int *)0x1608 < 8) {
      local_56[*(int *)0x1608] = local_56[*(int *)0x1608] + '\x01';
      *(int *)0x1608 = *(int *)0x1608 + 2;
    }
    FUN_144d_090a(0x93a);
    *(undefined2 *)0x1608 = 0;
    while (*(int *)0x1608 < 8) {
      iVar2 = FUN_144d_0864();
      if (iVar2 == local_56[*(int *)0x1608]) {
        *(int *)0x27a = *(int *)0x27a + 1;
      }
      *(int *)0x1608 = *(int *)0x1608 + 1;
    }
    if (*(int *)0x27a != 8) {
      FUN_144d_0a84(0x90,0,0);
    }
  }
  FUN_15f4_0010(0,acStack_a9 + 1);
  iVar2 = FUN_144d_079e(acStack_a9 + 1);
  if (acStack_a9[iVar2] != '\\') {
    FUN_144d_06f8(acStack_a9 + 1);
  }
  FUN_144d_073e(local_ee);
  FUN_144d_06f8(local_ee);
  while( true ) {
    do {
      FUN_144d_090a(0x958);
      local_136[0] = 5;
      FUN_144d_088c(local_136);
      iVar2 = FUN_144d_079e(local_136);
    } while (iVar2 == 0);
    FUN_144d_09a6(local_136);
    iVar2 = FUN_144d_07b6(local_136);
    if (iVar2 == 0) break;
    iVar2 = FUN_144d_0a51(local_ee);
    if (iVar2 != 0) {
      FUN_144d_090a(0x972);
      FUN_144d_0a84(0x90,0,0);
      FUN_15f4_0034(1);
      FUN_144d_0499(1);
    }
    while (iVar2 = FUN_144d_0a46(0x144d,local_162), iVar2 == 0) {
      if (((local_14d & 0x10) != 0) && (iVar2 = FUN_144d_0774(local_136), iVar2 == 0)) {
        FUN_144d_06f8(acStack_a9 + 1);
        FUN_144d_06f8(acStack_a9 + 1);
        FUN_15f4_0021(0,acStack_a9 + 1);
        goto LAB_1089_04b2;
      }
    }
    FUN_144d_090a(0x99c);
    FUN_144d_090a(0x9b6);
    FUN_144d_0a51(local_ee);
    while (iVar2 = FUN_144d_0a46(0x144d,local_162), iVar2 == 0) {
      if (((local_14d & 0x10) != 0) && (iVar2 = FUN_144d_0774(0x9ca), iVar2 != 0)) {
        FUN_144d_090a(local_144);
      }
    }
  }
LAB_1089_04b2:
  FUN_15f4_0034(1);
  uVar3 = &stack0x0000 == (undefined1 *)0x168;
  while( true ) {
    pcVar1 = (code *)swi(0x16);
    (*pcVar1)();
    if ((bool)uVar3) break;
    uVar3 = 1;
    pcVar1 = (code *)swi(0x16);
    (*pcVar1)();
  }
  FUN_144d_0499(0);
  return;
}

