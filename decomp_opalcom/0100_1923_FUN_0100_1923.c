
void FUN_0100_1923(void)

{
  int iVar1;
  int iVar2;
  undefined1 *unaff_SI;
  char *unaff_DI;
  undefined2 unaff_ES;
  undefined2 unaff_DS;
  
code_r0x00002923:
  do {
    iVar2 = -1;
    if ((*unaff_DI == '\0') && (unaff_DI[1] == '\0')) {
      *unaff_SI = 0;
      return;
    }
    do {
      iVar1 = iVar2 + 1;
      if (unaff_SI[iVar1] == '\n') goto FUN_0000_2949;
      iVar2 = iVar1;
    } while (unaff_DI[iVar1] == unaff_SI[iVar1]);
    unaff_DI = unaff_DI + 1;
  } while( true );
FUN_0000_2949:
  do {
    iVar2 = iVar2 + 1;
  } while (unaff_DI[iVar2] == ' ');
  if (unaff_DI[iVar2] == '=') {
    do {
      iVar2 = iVar2 + 1;
    } while (unaff_DI[iVar2] == ' ');
    FUN_0100_1722(unaff_DI + iVar2);
    return;
  }
  goto code_r0x00002923;
}

