
void FUN_0100_17ac(void)

{
  char *pcVar1;
  char *pcVar2;
  undefined2 uVar3;
  int iVar4;
  char *in_BX;
  char *pcVar5;
  char *pcVar6;
  undefined2 unaff_ES;
  undefined2 unaff_DS;
  char *in_stack_00000000;
  
  do {
    if (*(int *)0x629 <= (int)in_BX) {
      uRam00000143 = 0xffff;
      return;
    }
    pcVar5 = in_BX;
    uVar3 = FUN_0100_17d6();
    iVar4 = 5;
    pcVar6 = in_stack_00000000;
    do {
      if (iVar4 == 0) break;
      iVar4 = iVar4 + -1;
      pcVar2 = pcVar6;
      pcVar6 = pcVar6 + 1;
      pcVar1 = pcVar5;
      pcVar5 = pcVar5 + 1;
    } while (*pcVar1 == *pcVar2);
    if (iVar4 == 0) {
      uRam00000143 = uVar3;
      return;
    }
    in_BX = in_BX + 1;
  } while( true );
}

